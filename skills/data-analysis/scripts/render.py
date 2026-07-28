"""판정 JSON을 사람이 읽는 한 장으로 옮긴다.

🔴 **이 파일은 계산하지 않는다.** 모든 숫자는 `analyze.py` 가 만든 JSON 에서
그대로 온다. 렌더러가 계산을 시작하면 같은 값이 화면과 JSON 에서 달라진다.

만드는 것 둘 — 둘 다 같은 JSON 을 읽는다.

    HTML  타임리 `create_artifact` 로 인라인 렌더링. 스크린샷·데모영상용
    텍스트 콘솔·로그용. HTML 이 깨져도 숫자 결과는 남는다(Step 8 통과 기준)

**대시보드가 아니라 「한 장짜리 브리핑을 화면으로 그린 것」이다.**
필터도 정렬도 전 품목 표도 없다. 사용자를 다시 뒤지게 만들면
「오늘 이상한 몇 개만 낸다」는 이 제품의 전제가 무너진다.

    python scripts/render.py [보고서.json]
"""
from __future__ import annotations

import html
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from api import use_utf8_stdout  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "report.html"
OUTDIR = ROOT / "output"

단계순서 = ["산지", "도매", "소매"]


def esc(값) -> str:
    return html.escape(str(값), quote=False)


def 굵게(문장: str) -> str:
    """`**...**` 만 굵게 바꾼다. 그 외 마크업은 쓰지 않는다."""
    조각 = esc(문장).split("**")
    return "".join(c if i % 2 == 0 else f"<strong>{c}</strong>"
                   for i, c in enumerate(조각))


def 원(값) -> str:
    return f"{int(값):,}원" if isinstance(값, (int, float)) else "—"


# ── 유통 3단계 그림 ──────────────────────────────────────────────────
def 체인(단계들: list[dict]) -> str:
    """산지 → 도매 → 소매를 한 줄로 그린다.

    이 그림이 산문보다 나은 이유 — 「어디서 벌어졌나」는 **위치 정보**라서
    가로로 늘어놓으면 한눈에 읽힌다. 문장으로 쓰면 세 문장이 든다.
    """
    지도 = {d["단계"]: d for d in 단계들}
    칸 = []
    for i, 이름 in enumerate(단계순서):
        d = 지도.get(이름, {"관측": "자료없음"})
        관측 = d.get("관측", "자료없음")
        # 🔴 「평년의 1.9배」가 아니라 「2,400 → 5,040원 (+110%)」로 쓴다.
        #    의사결정자는 비율보다 금액에 먼저 반응한다.
        if d.get("올해") and d.get("평년평균"):
            율 = round((d["올해"] / d["평년평균"] - 1) * 100)
            값 = (f'<div class="px">{d["평년평균"]:,} → '
                 f'<b>{d["올해"]:,}원</b></div>'
                 f'<div class="pct">{"+" if 율 >= 0 else ""}{율}%</div>')
        elif d.get("올해"):
            값 = f'<div class="px">{d["올해"]:,}원</div><div class="pct">비교 불가</div>'
        else:
            값 = '<div class="px">—</div>'
        칸.append(
            f'<div class="stage {esc(관측)}">'
            f'<div class="nm">{esc(이름)}</div>{값}</div>'
        )
        if i < len(단계순서) - 1:
            칸.append('<div class="arrow">→</div>')
    return f'<div class="chain">{"".join(칸)}</div>'


def 카드(p: dict, 순번: int) -> str:
    항목 = [
        '<div class="card">',
        '<div class="head">',
        f'<span class="no">{순번}위</span>'
        f'<span class="name">{esc(p["품목"])}</span>',
    ]
    if p.get("확인필요"):
        항목.append('<span class="flag">확인 필요</span>')
    항목.append("</div>")

    항목.append(f'<p class="verdict">{굵게(p["사람말"])}</p>')

    if p.get("단계추적"):
        항목.append(체인(p["단계추적"]))
    if p.get("해석"):
        항목.append(f'<p class="reading">{굵게(p["해석"])}</p>')

    for 제목, 열쇠 in [("확인해 보실 것", "확인사항"), ("저희가 모르는 것", "모르는것")]:
        값 = p.get(열쇠) or []
        if 값:
            줄 = "".join(f"<li>{굵게(v)}</li>" for v in 값)
            항목.append(f'<div class="block"><h3>{제목}</h3><ul>{줄}</ul></div>')

    항목.append("</div>")
    return "".join(항목)


def 근거표(보고서: dict) -> str:
    수집 = 보고서.get("수집", {})
    검증 = 보고서.get("검증", {})
    줄 = [
        ("데이터", "공공데이터포털 — 산지공판장 · 도매시장 정산 · 도소매 가격"),
        ("기준가", f"같은 품목·같은 지역·같은 등급의 과거 "
                 f"{보고서.get('설정', {}).get('기준가', {}).get('기준연수', '?')}년 같은 달"),
        ("판정", "올해 값이 그 관측들 사이에서 몇 번째인지. 임의 임계치를 쓰지 않음"),
        ("수집", f"{수집.get('건수', {})} · 호출 {수집.get('호출수', '?')}회"),
    ]
    if 검증.get("경고"):
        줄.append(("확인된 결손", " / ".join(검증["경고"][:3])))
    if 수집.get("실패"):
        줄.append(("수집 실패", f"{len(수집['실패'])}건 — 기록하고 계속 진행"))
    return "".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in 줄)


# ── 출력 ─────────────────────────────────────────────────────────────
def html으로(보고서: dict) -> str:
    판정들 = 보고서.get("우선검토", [])
    본문 = ("".join(카드(p, i) for i, p in enumerate(판정들, 1)) if 판정들 else
          '<div class="card none">평소와 다르게 움직인 품목이 없습니다.<br>'
          '오늘은 따로 보실 것이 없습니다.</div>')
    채움 = {
        "제목수": f" {len(판정들)}가지" if 판정들 else "",
        "기준일": 보고서.get("기준일", ""),
        "생성시각": 보고서.get("생성시각", "")[:16].replace("T", " "),
        "오늘한줄": 굵게(보고서.get("오늘한줄", "")),
        "카드들": 본문,
        "한계들": "".join(f"<li>{esc(x)}</li>" for x in 보고서.get("한계", [])),
        "근거표": 근거표(보고서),
    }
    out = TEMPLATE.read_text(encoding="utf-8")
    for k, v in 채움.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def 텍스트로(보고서: dict) -> str:
    """HTML 이 깨져도 남는 판. 콘솔·로그·검증용."""
    줄 = ["=" * 62,
         f"오늘 먼저 볼 것   기준일 {보고서.get('기준일')} "
         f"· {보고서.get('생성시각', '')[:16].replace('T', ' ')} 자동 생성",
         "=" * 62,
         "  " + 보고서.get("오늘한줄", "").replace("**", "")]
    판정들 = 보고서.get("우선검토", [])
    if not 판정들:
        줄.append("\n  평소와 다르게 움직인 품목이 없습니다.")
    for i, p in enumerate(판정들, 1):
        줄.append(f"\n{i}위  {p['품목']}" + ("   [확인 필요]" if p.get("확인필요") else ""))
        줄.append(f"    {p['사람말'].replace('**', '')}")
        if p.get("단계추적"):
            지도 = {d["단계"]: d for d in p["단계추적"]}
            칸 = []
            for n in 단계순서:
                d = 지도.get(n, {})
                if d.get("올해") and d.get("평년평균"):
                    율 = round((d["올해"] / d["평년평균"] - 1) * 100)
                    칸.append(f"{n} {d['평년평균']:,}→{d['올해']:,}원"
                              f"({'+' if 율 >= 0 else ''}{율}%)")
                elif d.get("올해"):
                    칸.append(f"{n} {d['올해']:,}원(비교불가)")
                else:
                    칸.append(f"{n} 자료없음")
            줄.append("    " + "  →  ".join(칸))
        if p.get("해석"):
            줄.append(f"    {p['해석'].replace('**', '')}")
        for 제목, 열쇠 in [("확인해 보실 것", "확인사항"), ("모르는 것", "모르는것")]:
            for v in (p.get(열쇠) or []):
                줄.append(f"      · [{제목}] {v.replace('**', '')}")
    줄.append("\n" + "-" * 62)
    for x in 보고서.get("한계", []):
        줄.append(f"  ※ {x}")
    return "\n".join(줄)


def main() -> None:
    use_utf8_stdout()
    경로 = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else OUTDIR / "report.json"
    if not 경로.exists():
        raise SystemExit(f"판정 JSON 이 없습니다: {경로}\n  먼저 run.py 를 실행하세요.")

    보고서 = json.loads(경로.read_text(encoding="utf-8"))
    OUTDIR.mkdir(parents=True, exist_ok=True)

    (OUTDIR / "report.html").write_text(html으로(보고서), encoding="utf-8")
    본문 = 텍스트로(보고서)
    (OUTDIR / "report.txt").write_text(본문, encoding="utf-8")

    print(본문)
    print(f"\n→ output/report.html · output/report.txt")


if __name__ == "__main__":
    main()
