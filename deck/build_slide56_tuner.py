"""발표자료를 **직접 만지면서 맞추는 조절기**를 만든다.

    python deck/build_deck_tuner.py     →  deck/deck_tuner.html

🔴 위치와 크기는 말로 주고받기 가장 비싼 종류다. 대시보드 조절기와 같은
   방식으로, 사람이 막대를 움직이면 왼쪽 화면이 바로 바뀌고 값이 상자에
   쌓인다. 값을 붙여 주면 그대로 코드에 옮긴다.

화면은 `presentation.html` 을 그대로 iframe 에 넣는다 — 사본을 만들면
진짜와 어긋난다. 조절값은 iframe 안 `<style id="tune">` 에만 쓴다.
"""
from __future__ import annotations

import json
import sys
import pathlib

DECK = pathlib.Path(__file__).resolve().parent
DOC = DECK / "presentation.html"
OUT = DECK / "slide56_tuner.html"

# (열쇠, 이름, 선택자, 속성, 최소, 최대, 기본, 단위, 묶음)
손잡이 = [
    ("colgap", "좌우 칸 사이",          ".two", "column-gap",        4, 30, 12, "mm", "5·6장 공통"),
    ("h3sz",   "소제목 크기",           ".two h3", "font-size",       9, 22, 15, "pt", "5·6장 공통"),
    ("h3gap",  "소제목 아래 간격",      ".two h3", "margin-bottom",   1, 20, 5, "mm", "5·6장 공통"),
    ("lisz",   "줄 글자 크기",          ".two li", "font-size",       8, 16, 11, "pt", "5·6장 공통"),
    ("lilh",   "줄 안 행간",            ".two li", "line-height",     1.2, 2.4, 1.6, "", "5·6장 공통"),

    ("o_lgap", "왼쪽 줄 사이",          ".out .list:not(.plain)", "gap", 0, 24, 1, "mm", "5장"),
    ("o_rgap", "오른쪽 줄 사이",        ".out .list.plain", "gap",     0, 24, 1, "mm", "5장"),
    ("o_gapt", "도시 상자 위 간격",     ".out .gap", "margin-top",     0, 24, 4, "mm", "5장"),
    ("o_gapp", "도시 상자 안 여백",     ".out .gap", "padding-top",    2, 16, 5, "mm", "5장"),
    ("o_capt", "맨 아래 설명 위 간격",  ".out .cap-under", "margin-top", 0, 16, 3, "mm", "5장"),

    ("m_lgap", "왼쪽 줄 사이",          ".lim .list.plain", "gap",     0, 30, 1, "mm", "6장"),
    ("m_rgap", "오른쪽 줄 사이",        ".lim .next", "gap",           0, 30, 3.9, "mm", "6장"),
    ("m_ngap", "오른쪽 번호 칸 너비",   ".lim .next li", "grid-template-columns", 6, 16, 9, "mm", "6장"),
    ("m_read", "맨 아래 결론 위 간격",  ".lim .readout", "padding-top", 2, 20, 5, "mm", "6장"),
    ("m_rsz",  "맨 아래 결론 크기",     ".lim .readout", "font-size",   8, 16, 12, "pt", "6장"),
]

배치 = [
    ("o_lpos", "5장 왼쪽 줄 세로", ".out .list:not(.plain)", "justify-content",
     [("flex-start", "위로"), ("space-between", "위아래로"), ("space-evenly", "고르게")],
     "space-between"),
    ("o_rpos", "5장 오른쪽 줄 세로", ".out .list.plain", "justify-content",
     [("flex-start", "위로"), ("space-between", "위아래로"), ("space-evenly", "고르게")],
     "space-between"),
    ("m_lpos", "6장 왼쪽 줄 세로", ".lim .list.plain", "justify-content",
     [("flex-start", "위로"), ("space-between", "위아래로"), ("space-evenly", "고르게")],
     "space-between"),
    ("m_rpos", "6장 오른쪽 줄 세로", ".lim .next", "justify-content",
     [("flex-start", "위로"), ("space-between", "위아래로"), ("space-evenly", "고르게")],
     "space-between"),
]


TEMPLATE = """<title>5·6장 조절기</title>
<style>
:root { --ink:#3d3e42; --soft:#9a9ca2; --rule:#c2c4ca; --blue:#6b84f5; --deep:#4a63d8; }
* { box-sizing:border-box; }
body { margin:0; background:#e9ebef; color:var(--ink);
       font-family:"Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif;
       display:grid; grid-template-columns:1fr 320px; height:100vh; }
#stage { overflow:hidden; }
iframe { width:100%; height:100%; border:0; background:#b9bcc4; display:block; }
aside { background:#fff; border-left:1px solid var(--rule);
        display:flex; flex-direction:column; min-height:0; }
aside h1 { margin:0; padding:13px 16px; font-size:15px; border-bottom:1px solid var(--rule); }
aside h1 small { display:block; font-weight:400; font-size:11.5px; color:var(--soft);
                 margin-top:3px; line-height:1.5; }
#knobs { flex:1; overflow-y:auto; padding:4px 16px 16px; }
.grp { font-size:11px; font-weight:700; color:var(--deep); letter-spacing:.04em;
       margin:14px 0 2px; padding-top:8px; border-top:1px solid #eef0f3; }
.grp:first-child { border-top:0; margin-top:6px; }
.k { padding:7px 0; }
.k .t { display:flex; justify-content:space-between; align-items:baseline;
        font-size:12.5px; margin-bottom:4px; }
.k .t b { font-weight:600; }
.k .t output { font-variant-numeric:tabular-nums; color:var(--deep); font-weight:600; }
.k input[type=range] { width:100%; accent-color:var(--blue); }
.seg { display:flex; gap:4px; margin-top:4px; flex-wrap:wrap; }
.seg button { flex:1; min-width:52px; font:inherit; font-size:11.5px; padding:5px 4px;
              border:1px solid var(--rule); background:#fff; cursor:pointer; }
.seg button[aria-pressed="true"] { background:var(--blue); border-color:var(--blue); color:#fff; }
footer { border-top:1px solid var(--rule); padding:12px 16px;
         display:flex; flex-direction:column; gap:8px; }
#outbox { width:100%; height:110px; resize:vertical; font-size:11.5px; line-height:1.6;
          font-family:Consolas,monospace; color:#2f3136; background:#f6f7f9;
          border:1px solid var(--rule); padding:8px; white-space:pre; overflow:auto; }
button.go { background:var(--blue); border:1px solid var(--blue); color:#fff;
            font:inherit; font-size:13px; padding:8px 14px; cursor:pointer; }
button.go:hover { background:var(--deep); }
button.pl { font:inherit; font-size:13px; padding:8px 14px; cursor:pointer;
            border:1px solid var(--rule); background:#fff; }
#msg { font-size:11.5px; color:#2f8f5b; min-height:1.2em; }
.jump { display:flex; gap:6px; margin-top:8px; }
.jump button { flex:1; font:inherit; font-size:12px; padding:5px; cursor:pointer;
               border:1px solid var(--rule); background:#fff; }
.jump button:hover { background:#f2f4f8; }
</style>

<div id="stage"><iframe id="v" title="발표자료 미리보기"></iframe></div>

<aside>
  <h1>5·6장 조절기
    <small>5·6장만 다룹니다. 아래 버튼으로 장을 오갈 수 있습니다.
      값은 상자에 쌓이니 그대로 채팅에 붙여 주세요.</small>
    <div class="jump"><button data-go="4">5장으로</button><button data-go="5">6장으로</button></div></h1>
  <div id="knobs"></div>
  <footer>
    <textarea id="outbox" readonly spellcheck="false" aria-label="맞춘 값"></textarea>
    <div style="display:flex;gap:8px">
      <button class="go" id="copy" style="flex:1">전체 선택 + 복사</button>
      <button class="pl" id="reset">처음으로</button>
    </div>
    <div id="msg"></div>
  </footer>
</aside>

<script id="doc" type="text/plain">__DOC__</script>
<script>
const 손잡이 = __KNOBS__, 배치 = __POS__;
const 값 = {}, 고름 = {};
손잡이.forEach(k => 값[k.id] = k.def);
배치.forEach(k => 고름[k.id] = k.def);

const v = document.getElementById("v");

function css() {
  const 줄 = 손잡이.map(k => {
    const p = k.prop;
    // padding-top / padding-left 는 위아래·좌우 짝을 함께 준다
    if (p === "padding-top")  return `${k.sel}{padding-top:${값[k.id]}${k.unit} !important;padding-bottom:${값[k.id]}${k.unit} !important}`;
    if (p === "padding-left") return `${k.sel}{padding-left:${값[k.id]}${k.unit} !important;padding-right:${값[k.id]}${k.unit} !important}`;
    if (p === "grid-template-columns")
      return `${k.sel}{grid-template-columns:${값[k.id]}${k.unit} 1fr !important}`;
    return `${k.sel}{${p}:${값[k.id]}${k.unit} !important}`;
  });
  배치.forEach(k => 줄.push(`${k.sel}{${k.prop}:${고름[k.id]} !important}`));
  return 줄.join("\\n");
}
function 칠하기() {
  const d = v.contentDocument;
  // 🔴 `load` 리스너만 믿으면 안 된다. srcdoc 은 문서가 커질수록 타이밍이
  //    달라져, 리스너를 붙이기 전에 이미 로드가 끝나 첫 칠하기가 날아간다.
  //    **화면에 .slide 가 들어왔는지 직접 확인**하고, 아니면 다시 시도한다.
  if (!d || !d.querySelector(".slide")) { setTimeout(칠하기, 80); return; }
  let s = d.getElementById("tune");
  if (!s) {
    s = d.createElement("style"); s.id = "tune";
    (d.head || d.documentElement).appendChild(s);
  }
  s.textContent = css();
  손잡이.forEach(k => {
    const o = document.getElementById("o_" + k.id);
    if (o) o.value = 값[k.id] + k.unit;
  });
  document.getElementById("outbox").value = 요약();
}
function 요약() {
  const 줄 = 손잡이.filter(k => 값[k.id] !== k.def)
    .map(k => `${k.grp} ${k.name}: ${값[k.id]}${k.unit}   (${k.sel} · ${k.prop})`);
  배치.filter(k => 고름[k.id] !== k.def).forEach(k =>
    줄.push(`${k.name}: ${고름[k.id]}   (${k.sel} · ${k.prop})`));
  return 줄.length ? 줄.join("\\n") : "아직 바꾼 값이 없습니다.";
}

let html = "", 이전묶음 = "";
손잡이.forEach(k => {
  if (k.grp !== 이전묶음) { html += `<div class="grp">${k.grp}</div>`; 이전묶음 = k.grp; }
  html += `<div class="k"><div class="t"><b>${k.name}</b>` +
          `<output id="o_${k.id}">${k.def}${k.unit}</output></div>` +
          `<input type="range" id="r_${k.id}" min="${k.min}" max="${k.max}" ` +
          `step="0.1" value="${k.def}"></div>`;
});
html += `<div class="grp">세로 배치</div>`;
배치.forEach(k => {
  html += `<div class="k"><div class="t"><b>${k.name}</b></div><div class="seg">` +
    k.opts.map(([val, lab]) =>
      `<button data-p="${k.id}" data-v="${val}" aria-pressed="${val === k.def}">${lab}</button>`).join("") +
    `</div></div>`;
});
document.getElementById("knobs").innerHTML = html;

손잡이.forEach(k => document.getElementById("r_" + k.id)
  .addEventListener("input", e => { 값[k.id] = +e.target.value; 칠하기(); }));
document.querySelectorAll(".seg button").forEach(b =>
  b.addEventListener("click", () => {
    const p = b.dataset.p;
    고름[p] = b.dataset.v;
    document.querySelectorAll(`.seg button[data-p="${p}"]`).forEach(x =>
      x.setAttribute("aria-pressed", x === b));
    칠하기();
  }));

document.getElementById("reset").addEventListener("click", () => {
  손잡이.forEach(k => { 값[k.id] = k.def; document.getElementById("r_" + k.id).value = k.def; });
  배치.forEach(k => {
    고름[k.id] = k.def;
    document.querySelectorAll(`.seg button[data-p="${k.id}"]`).forEach(x =>
      x.setAttribute("aria-pressed", x.dataset.v === k.def));
  });
  칠하기();
});
document.getElementById("copy").addEventListener("click", async () => {
  const box = document.getElementById("outbox");
  box.focus(); box.select(); box.setSelectionRange(0, box.value.length);
  let 됨 = false;
  try { await navigator.clipboard.writeText(box.value); 됨 = true; } catch (e) {}
  if (!됨) { try { 됨 = document.execCommand("copy"); } catch (e) {} }
  document.getElementById("msg").textContent = 됨
    ? "복사했습니다 — 채팅에 붙여 넣으세요"
    : "복사가 막혔습니다 — 위 상자가 선택돼 있으니 Ctrl+C 를 누르세요";
  setTimeout(() => document.getElementById("msg").textContent = "", 5000);
});
// 리스너 · 즉시 호출 둘 다 건다. 어느 쪽이 먼저든 칠하기가 스스로 기다린다
document.querySelectorAll(".jump button").forEach(b =>
  b.addEventListener("click", () => {
    const d = v.contentDocument; if (!d) return;
    const s = d.querySelectorAll(".slide")[+b.dataset.go];
    if (s) s.scrollIntoView({ behavior: "smooth", block: "start" });
  }));
v.addEventListener("load", 칠하기);
v.srcdoc = document.getElementById("doc").textContent;
칠하기();
</script>
"""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not DOC.exists():
        print(f"🔴 {DOC.name} 이 없습니다.")
        raise SystemExit(1)
    문서 = DOC.read_text(encoding="utf-8").replace("</script>", "<\\/script>")
    표 = [{"id": i, "name": n, "sel": s, "prop": p, "min": lo, "max": hi,
          "def": d, "unit": u, "grp": g}
          for i, n, s, p, lo, hi, d, u, g in 손잡이]
    pos = [{"id": i, "name": n, "sel": s, "prop": p, "opts": o, "def": d}
           for i, n, s, p, o, d in 배치]
    OUT.write_text(
        TEMPLATE.replace("__DOC__", 문서)
                .replace("__KNOBS__", json.dumps(표, ensure_ascii=False))
                .replace("__POS__", json.dumps(pos, ensure_ascii=False)),
        encoding="utf-8")
    print(f"→ {OUT.name} ({OUT.stat().st_size/1024:.0f}KB) · "
          f"막대 {len(표)}개 · 배치 {len(pos)}개")


if __name__ == "__main__":
    main()
