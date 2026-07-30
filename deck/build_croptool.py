"""포스터에 심은 화면 사진을 **끌어서 맞추는 도구**를 만든다.

    python deck/build_croptool.py     →  deck/croptool.html

🔴 왜 만드는가 — 자르기·확대는 **말로 지시하기 가장 어려운 종류**다.
   「조금만 위로」가 몇 %인지 서로 모른 채 왕복하면 시간만 든다.
   사람이 직접 끌어 맞추고, 도구가 **CSS 값을 대신 읽어 준다.**

사진은 `onepager.html` 에 이미 심어 둔 data URI 를 그대로 꺼내 쓴다 —
따로 들고 있으면 포스터와 어긋난다.

도구가 내놓는 값은 포스터의 세 속성 그대로다.

    높이   .shot .im 의 height (mm)
    확대   background-size (%) — 100%가 「폭에 맞춤」
    위치   background-position (X% Y%)
"""
from __future__ import annotations

import base64
import io
import re
import sys
import pathlib

from PIL import Image

DECK = pathlib.Path(__file__).resolve().parent
POSTER = DECK / "onepager.html"
OUT = DECK / "croptool.html"

# 포스터의 실제 칸 — 여기 바뀌면 도구도 같이 바꾼다
칸 = [
    ("board", "대시보드", 88, 52, 20, 110),
    ("reg", "등록 목록", 88, 34, 15, 80),
]


def 사진꺼내기() -> dict[str, str]:
    html = POSTER.read_text(encoding="utf-8")
    찾음 = {}
    for 키, 표시 in (("board", "대시보드"), ("reg", "등록")):
        m = re.search(re.escape(f"/* SHOT:{표시} */") + r"\s*url\((data:[^)]+)\)",
                      html)
        if not m:
            print(f"🔴 {POSTER.name} 에서 {표시} 사진을 찾지 못했습니다.")
            print("   먼저 python deck/build_shot.py 를 돌리세요.")
            raise SystemExit(1)
        찾음[키] = m.group(1)
    return 찾음


TEMPLATE = """<title>포스터 사진 맞추기</title>
<style>
:root {
  --paper: #f4f5f7; --ink: #3d3e42; --ink-mid: #6e7075; --ink-soft: #9a9ca2;
  --blue: #6b84f5; --blue-deep: #4a63d8; --rule: #c2c4ca; --card: #e8eaee;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 28px 20px 60px; background: var(--paper); color: var(--ink);
  font-family: "Malgun Gothic", "Apple SD Gothic Neo", system-ui, sans-serif;
}
.wrap { max-width: 760px; margin: 0 auto; }
h1 { font-size: 22px; margin: 0 0 6px; letter-spacing: -0.02em; }
.lead { color: var(--ink-soft); font-size: 13px; line-height: 1.7; margin: 0 0 24px; }
.lead b { color: var(--ink-mid); }

.panel { background: #fff; border: 1px solid var(--rule); margin-bottom: 22px; }
.panel > h2 {
  margin: 0; padding: 12px 16px; font-size: 15px; border-bottom: 1px solid var(--rule);
  display: flex; align-items: center; gap: 8px;
}
.panel > h2 i { width: 9px; height: 9px; border-radius: 50%; background: var(--blue); }
.panel > h2 small { color: var(--ink-soft); font-weight: 400; font-size: 12px; }

.stage { padding: 16px; }
.frame {
  position: relative; width: 100%; overflow: hidden; cursor: grab;
  border: 1px solid var(--rule); background: #fff;
  background-repeat: no-repeat; touch-action: none;
}
.frame.drag { cursor: grabbing; }
.frame::after {
  content: "끌어서 옮기기"; position: absolute; right: 8px; bottom: 6px;
  font-size: 11px; color: #fff; background: rgba(0,0,0,.42);
  padding: 2px 7px; border-radius: 3px; pointer-events: none;
}
.frame.moved::after { display: none; }

.ctrl { display: grid; grid-template-columns: 62px 1fr 66px; gap: 10px;
        align-items: center; margin-top: 12px; font-size: 13px; }
.ctrl label { color: var(--ink-mid); }
.ctrl input[type=range] { width: 100%; accent-color: var(--blue); }
.ctrl output { text-align: right; font-variant-numeric: tabular-nums;
               color: var(--ink); font-weight: 600; }

.row { display: flex; gap: 8px; margin-top: 14px; }
button {
  font: inherit; font-size: 13px; padding: 7px 14px; border: 1px solid var(--rule);
  background: #fff; color: var(--ink); cursor: pointer; border-radius: 0;
}
button:hover { background: var(--card); }
button:focus-visible { outline: 2px solid var(--blue); outline-offset: 2px; }
button.go { background: var(--blue); border-color: var(--blue); color: #fff; }
button.go:hover { background: var(--blue-deep); }

.out {
  position: sticky; bottom: 0; background: #2f3136; color: #d6d8dd;
  padding: 14px 16px; font-family: ui-monospace, Consolas, monospace;
  font-size: 12.5px; line-height: 1.8; white-space: pre-wrap; word-break: break-all;
}
.out .k { color: #8fa4ff; }
.done { color: #7ddb9a; font-size: 12px; margin-left: 8px; }
</style>

<div class="wrap">
  <h1>포스터 사진 맞추기</h1>
  <p class="lead">
    아래 칸은 <b>포스터에 실제로 들어가는 크기</b> 그대로입니다.
    사진을 끌어서 옮기고, 막대로 확대·높이를 맞추세요.<br>
    다 됐으면 맨 아래 상자의 <b>「값 복사」를 눌러 채팅에 붙여</b> 주세요. 그대로 반영합니다.
  </p>

  __PANELS__

  <div class="out" id="out"></div>
  <div class="row">
    <button class="go" id="copy">값 복사</button>
    <span class="done" id="done"></span>
  </div>
</div>

<script>
const 칸들 = __SPEC__;
const MM = 4.6;                       // 화면에서 1mm 를 몇 px 로 그릴까

const 상태 = {};
칸들.forEach(c => {
  상태[c.id] = { h: c.h, zoom: 100, x: 50, y: 0 };
});

function 그리기(id) {
  const c = 칸들.find(v => v.id === id), s = 상태[id];
  const f = document.getElementById("f_" + id);
  f.style.height = (s.h * MM) + "px";
  f.style.backgroundSize = s.zoom + "% auto";
  f.style.backgroundPosition = s.x + "% " + s.y + "%";
  document.getElementById("oh_" + id).value = s.h + "mm";
  document.getElementById("oz_" + id).value = s.zoom + "%";
  적기();
}

function 적기() {
  const 줄 = 칸들.map(c => {
    const s = 상태[c.id];
    return `<span class="k">${c.name}</span>  높이 ${s.h}mm · 확대 ${s.zoom}% · 위치 ${s.x}% ${s.y}%`;
  });
  document.getElementById("out").innerHTML = 줄.join("\\n");
}

function 원문() {
  return 칸들.map(c => {
    const s = 상태[c.id];
    return `${c.name}: 높이 ${s.h}mm · 확대 ${s.zoom}% · 위치 ${s.x}% ${s.y}%`;
  }).join("\\n");
}

칸들.forEach(c => {
  const f = document.getElementById("f_" + c.id);
  f.style.backgroundImage = "url(" + c.src + ")";
  f.style.width = "100%";

  // 끌어서 옮기기 — 넘치는 만큼만 움직인다
  let 끄는중 = false, px = 0, py = 0;
  f.addEventListener("pointerdown", e => {
    끄는중 = true; px = e.clientX; py = e.clientY;
    f.classList.add("drag", "moved"); f.setPointerCapture(e.pointerId);
  });
  f.addEventListener("pointermove", e => {
    if (!끄는중) return;
    const s = 상태[c.id];
    const w = f.clientWidth, h = f.clientHeight;
    const iw = w * s.zoom / 100, ih = iw * c.ratio;
    const ox = iw - w, oy = ih - h;
    if (ox > 1) s.x = Math.min(100, Math.max(0, s.x - (e.clientX - px) / ox * 100));
    if (oy > 1) s.y = Math.min(100, Math.max(0, s.y - (e.clientY - py) / oy * 100));
    px = e.clientX; py = e.clientY;
    상태[c.id] = { ...s, x: Math.round(s.x), y: Math.round(s.y) };
    그리기(c.id);
  });
  const 놓기 = () => { 끄는중 = false; f.classList.remove("drag"); };
  f.addEventListener("pointerup", 놓기);
  f.addEventListener("pointercancel", 놓기);

  document.getElementById("z_" + c.id).addEventListener("input", e => {
    상태[c.id].zoom = +e.target.value; 그리기(c.id);
  });
  document.getElementById("h_" + c.id).addEventListener("input", e => {
    상태[c.id].h = +e.target.value; 그리기(c.id);
  });
  document.getElementById("r_" + c.id).addEventListener("click", () => {
    상태[c.id] = { h: c.h, zoom: 100, x: 50, y: 0 };
    document.getElementById("z_" + c.id).value = 100;
    document.getElementById("h_" + c.id).value = c.h;
    f.classList.remove("moved");
    그리기(c.id);
  });

  그리기(c.id);
});

document.getElementById("copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(원문());
    document.getElementById("done").textContent = "복사했습니다 — 채팅에 붙여 넣으세요";
  } catch {
    document.getElementById("done").textContent =
      "복사가 막혔습니다 — 위 상자의 글을 직접 긁어 주세요";
  }
  setTimeout(() => { document.getElementById("done").textContent = ""; }, 4000);
});
</script>
"""

PANEL = """  <div class="panel">
    <h2><i></i>{표시} <small>포스터 칸 {폭}mm 폭</small></h2>
    <div class="stage">
      <div class="frame" id="f_{키}"></div>
      <div class="ctrl">
        <label for="z_{키}">확대</label>
        <input type="range" id="z_{키}" min="100" max="320" step="2" value="100">
        <output id="oz_{키}">100%</output>
        <label for="h_{키}">칸 높이</label>
        <input type="range" id="h_{키}" min="{최소}" max="{최대}" step="1" value="{높이}">
        <output id="oh_{키}">{높이}mm</output>
      </div>
      <div class="row"><button id="r_{키}">처음으로</button></div>
    </div>
  </div>"""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    사진 = 사진꺼내기()

    패널 = "\n".join(
        PANEL.format(키=키, 표시=표시, 폭=폭, 높이=높이, 최소=최소, 최대=최대)
        for 키, 표시, 폭, 높이, 최소, 최대 in 칸)

    # 🔴 ratio 는 **사진 자체의** 세로/가로다. 칸의 비율이 아니다 —
    #    끌 때 「세로로 얼마나 넘치는가」를 재려면 사진 비율이어야 한다.
    조각 = []
    for 키, 표시, 폭, 높이, _, _ in 칸:
        raw = base64.b64decode(사진[키].split("base64,", 1)[1])
        w, h = Image.open(io.BytesIO(raw)).size
        print(f"  {표시:8} {w}×{h}px · 칸 {폭}×{높이}mm")
        조각.append(f'  {{id:"{키}", name:"{표시}", h:{높이}, ratio:{h/w:.4f},'
                   f' src:"{사진[키]}"}}')
    spec = "[\n" + ",\n".join(조각) + "\n]"

    OUT.write_text(TEMPLATE.replace("__PANELS__", 패널).replace("__SPEC__", spec),
                   encoding="utf-8")
    print(f"→ {OUT.name} ({OUT.stat().st_size/1024:.0f}KB)")
    print("  브라우저로 열어 맞춘 뒤 「값 복사」를 눌러 채팅에 붙이세요.")


if __name__ == "__main__":
    main()
