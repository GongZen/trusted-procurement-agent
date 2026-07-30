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
OUT = DECK / "deck_tuner.html"

# (열쇠, 이름, 선택자, 속성, 최소, 최대, 기본, 단위, 묶음)
손잡이 = [
    ("pad",    "장 안쪽 여백",        ".slide", "padding-top",  8, 30, 15, "mm", "전체"),
    ("padx",   "장 좌우 여백",        ".slide", "padding-left", 10, 34, 22, "mm", "전체"),
    ("h2",     "장 제목 크기",        ".head h2", "font-size",  16, 40, 30, "pt", "전체"),

    ("thin",   "표지 윗줄 크기",      ".title .thin",  "font-size", 12, 34, 24, "pt", "1장"),
    ("thick",  "표지 굵은 줄 크기",   ".title .thick", "font-size", 22, 60, 44, "pt", "1장"),
    ("desc",   "표지 설명 크기",      ".title .desc",  "font-size", 7, 14, 9.5, "pt", "1장"),
    ("descgap", "굵은 줄 ↔ 설명",     ".title .desc",  "margin-top", 0, 20, 6, "mm", "1장"),
    ("numv",   "핵심 넘버 크기",      ".num .v",       "font-size", 16, 40, 26, "pt", "1장"),
    ("numpad", "넘버 띠 위아래 여백", ".numbers", "padding-top",   2, 16, 6, "mm", "1장"),

    ("qgap",   "2장 두 블록 사이",    ".slide.q .blocks", "gap",   2, 30, 8, "mm", "2장"),
    ("cardpad", "2장 카드 안 여백",   ".card .body", "padding-top", 2, 14, 5, "mm", "2장"),

    ("lgap",   "3장 칸 사이",         ".layers", "gap",            2, 20, 6, "mm", "3장"),
    ("lpad",   "3장 칸 안 여백",      ".layer",  "padding-top",    3, 18, 7, "mm", "3장"),
    ("lnm",    "3장 단계 이름 크기",  ".layer .nm", "font-size",  12, 28, 19, "pt", "3장"),

    ("stepgap", "4장 단계 사이",      ".steps", "gap",             1, 12, 2.6, "mm", "4장"),
    ("steppad", "4장 단계 안 여백",   ".step",  "padding-top",     1, 10, 3, "mm", "4장"),

    ("listgap", "5·6장 줄 사이(최소)", ".list", "gap",             1, 20, 3, "mm", "5·6장"),
    ("listsz",  "5·6장 글자 크기",    ".list li", "font-size",     8, 16, 11, "pt", "5·6장"),
    ("nextgap", "6장 오른쪽 줄 사이", ".next", "gap",              1, 20, 3, "mm", "5·6장"),
]

# 세로 배치는 값이 아니라 **고름**이라 따로 둔다
배치 = [
    ("qpos", "2장 블록 세로 위치", ".slide.q .blocks", "justify-content",
     [("flex-start", "위로"), ("center", "가운데"), ("space-between", "위아래로"),
      ("space-evenly", "고르게")], "flex-start"),
    ("lpos", "5·6장 줄 세로 배치", ".list", "justify-content",
     [("flex-start", "위로"), ("space-between", "위아래로"),
      ("space-evenly", "고르게")], "space-between"),
    ("cpos", "1장 표지 세로 위치", ".cover", "justify-content",
     [("center", "가운데"), ("flex-start", "위로"), ("space-between", "위아래로")],
     "center"),
]

TEMPLATE = """<title>발표자료 배치 조절기</title>
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
</style>

<div id="stage"><iframe id="v" title="발표자료 미리보기"></iframe></div>

<aside>
  <h1>발표자료 배치 조절기
    <small>막대를 움직이면 왼쪽이 바로 바뀝니다. 왼쪽 화면은 스크롤해서
      6장을 다 보실 수 있습니다. 값은 아래 상자에 쌓입니다.</small></h1>
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
