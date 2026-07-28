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
    """🔴 이름과 달리 **굵게 하지 않는다.** `**` 표시만 걷어내고 평문으로 낸다.

    처음에는 중요한 대목을 굵게 했는데, 한 문장에 굵은 곳이 서너 군데 생기자
    **강조가 강조로 읽히지 않았다.** 전부 굵으면 아무것도 굵지 않은 것과 같다.

    그래서 문장에서는 굵기를 쓰지 않는다. 위계는 **자리와 크기**가 만든다 —
    가장 큰 숫자가 머리에 있고, 품목명이 카드 머리에 있고, 증감률이 오른쪽
    끝에 있다. 함수 이름은 호출부를 건드리지 않으려고 그대로 둔다.
    """
    return esc(문장).replace("**", "")


# ── 시계열 그래프 ────────────────────────────────────────────────────
def 그래프(점들: list[dict], 대상월: str, 구간이름: str = "",
         전국: list[dict] | None = None) -> str:
    """월별 가격 추이를 면적 그래프로 그린다.

    문장은 「지금 어디쯤인가」를 말하고, 이 선은 「어떤 길로 여기 왔는가」를
    보여준다. 둘은 대체 관계가 아니다.

    🔑 **같은 달만 점으로 찍는다.** 계절 진폭이 워낙 커서 전 구간을 이으면
    톱니만 보이고 연도 간 차이가 묻힌다. 우리가 판정한 것도 같은 달끼리의
    비교이므로 그림과 판정이 어긋나지 않아야 한다.
    """
    같은달 = [p for p in 점들 if p["ym"][4:] == 대상월]
    if len(같은달) < 3:
        return ""

    값 = [p["값"] for p in 같은달]
    연도 = [p["ym"][:4] for p in 같은달]
    전국맵 = {q["ym"][:4]: q["값"] for q in (전국 or []) if q["ym"][4:] == 대상월}
    전국값 = [전국맵.get(y) for y in 연도]
    쓸전국 = [v for v in 전국값 if v]
    최소 = min(값 + 쓸전국)
    최대 = max(값 + 쓸전국)
    폭 = (최대 - 최소) or 1
    W, H, PAD = 100, 56, 4

    def 좌표(i: int, v: float) -> tuple[float, float]:
        x = PAD + (W - PAD * 2) * (i / max(len(값) - 1, 1))
        y = PAD + (H - PAD * 2) * (1 - (v - 최소) / 폭)
        return round(x, 2), round(y, 2)

    점자리 = [좌표(i, v) for i, v in enumerate(값)]  # 끝점 표식은 두지 않는다 — 선만으로 읽힌다
    선 = " ".join(f"{x},{y}" for x, y in 점자리)
    # 전국 중앙값 선 — 한 구간만 그리면 그 선이 높은지 낮은지 알 수 없다
    전국선 = ""
    if len(쓸전국) >= 3:
        자리 = [좌표(i, v) for i, v in enumerate(전국값) if v]
        전국선 = ('<polyline class="med" points="'
                + " ".join(f"{x},{y}" for x, y in 자리) + '"/>')
    면 = f"{PAD},{H - PAD} {선} {점자리[-1][0]},{H - PAD}"
    끝x, 끝y = 점자리[-1]
    올해 = 같은달[-1]
    처음 = 같은달[0]

    눈금 = "".join(
        f'<line x1="{PAD}" y1="{round(PAD + (H - PAD * 2) * f, 2)}" '
        f'x2="{W - PAD}" y2="{round(PAD + (H - PAD * 2) * f, 2)}" '
        f'class="grid"/>' for f in (0, 0.5, 1))

    라벨 = (f'<span>{처음["ym"][:4]}년 {int(대상월)}월 {처음["값"]:,}원</span>'
          f'<span class="now">{올해["ym"][:4]}년 {올해["값"]:,}원</span>')

    return (
        f'<figure class="chart">'
        f'<figcaption><span class="cap">{int(대상월)}월 가격 · 최근 {len(값)}년'
        f'</span>{f"<span class='seg'>{esc(구간이름)}</span>" if 구간이름 else ""}'
        f'</figcaption>'
        f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" '
        f'role="img" aria-label="{int(대상월)}월 가격 추이">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" class="s0"/><stop offset="100%" class="s1"/>'
        f'</linearGradient></defs>'
        f'{눈금}'
        f'<polygon class="area" points="{면}"/>'
        f'{전국선}'
        f'<polyline class="line" points="{선}"/>'
        f'</svg>'
        f'<div class="axis">{라벨}</div>'
        f'<div class="legend-line">'
        f'<span class="lg pick">{esc(구간이름.split(" · ")[0])}</span>'
        + (f'<span class="lg med">같은 조건 전국 중앙값</span>' if 전국선 else "")
        + f'</div>'
        f'</figure>')


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
    for 이름 in 단계순서:
        d = 지도.get(이름, {"관측": "자료없음"})
        관측 = d.get("관측", "자료없음")
        # 🔴 「평년의 1.9배」가 아니라 「2,400 → 5,040원 +110%」로 쓴다.
        #    의사결정자는 비율보다 금액에 먼저 반응한다.
        if d.get("올해") and d.get("평년평균"):
            표기, 방향 = 증감(d["평년평균"], d["올해"])
            값 = (f'<span class="was fig">평년 {d["평년평균"]:,}원</span>'
                 f'<span class="now fig">{d["올해"]:,}원</span>'
                 f'<span class="dt fig">{표기}</span>')
            클래스 = f"{esc(관측)} {방향}"
        elif d.get("올해"):
            값 = (f'<span class="was">비교할 과거 없음</span>'
                 f'<span class="now fig">{d["올해"]:,}원</span>')
            클래스 = "비교불가"
        else:
            값 = '<span class="was">자료 없음</span><span class="now">—</span>'
            클래스 = "자료없음"
        칸.append(f'<div class="step {클래스}">'
                  f'<span class="nm">{esc(이름)}</span>{값}</div>')
    return f'<div class="chain">{"".join(칸)}</div>'


def 증감(전, 후) -> tuple[str, str]:
    """(표기, 방향). 방향은 CSS 클래스로 쓰인다."""
    if not 전 or not 후:
        return "—", "flat"
    율 = round((후 / 전 - 1) * 100)
    방향 = "up" if 율 > 0 else ("down" if 율 < 0 else "flat")
    return f"{'+' if 율 > 0 else ''}{율}%", 방향


def 카드(p: dict, 순번: int, 전체: int, 대상월: str) -> str:
    """한 화면에 하나씩. 좌우로 넘긴다."""
    표기, 방향 = 증감(p.get("평년평균"), p.get("올해"))
    항목 = [
        f'<div class="entry" role="group" aria-roledescription="slide" '
        f'aria-label="{순번} / {전체}">',
        '<div class="entry-head">',
        f'<span class="rank fig">{순번}</span>'
        f'<span class="item">{esc(p["품목"])}</span>',
    ]
    항목.append(f'<span class="move fig {방향}">{표기}</span></div>')

    # ── 왼쪽: 설명 + 큰 숫자 하나 ──
    왼 = [f'<p class="say">{굵게(p["사람말"])}</p>']
    c = p.get("최고")
    if c:
        # 스탯과 해석을 한 덩어리로 둔다 — 숫자와 그 숫자에 대한 해석이
        # 따로 놓이면 눈이 두 번 왕복한다
        속 = [f'<span class="k">{esc(c["지역"])} {esc(c["품종"])} '
             f'{esc(c["등급"])}</span>'
             f'<span class="v fig">{esc(c["증감"]).rstrip("%")}'
             f'<span class="u">%</span></span>'
             f'<span class="sub fig">{c["평년"]:,}원 → {c["올해"]:,}원</span>']
        if p.get("해석"):
            속.append(f'<p class="read">{굵게(p["해석"])}</p>')
        왼.append(f'<div class="stat">{"".join(속)}</div>')
    elif p.get("해석"):
        왼.append(f'<div class="stat"><p class="read">{굵게(p["해석"])}</p></div>')
    항목.append(f'<div class="col-l">{"".join(왼)}</div>')

    # ── 오른쪽: 그래프 + 그 아래 빈 자리에 「가장 싼 도시」 ──
    오른 = []
    if p.get("시계열"):
        오른.append(그래프(p["시계열"], 대상월, p.get("그린구간", ""),
                        p.get("전국선")))
    b = p.get("도시")
    if b:
        오른.append(
            '<div class="buy">'
            f'<span class="k">같은 조건에서 가장 싼 도시 · {esc(b["조건"])}</span>'
            f'<span class="row"><b>{esc(b["싼곳"]["지역"])}</b>'
            f'<span class="fig">{b["싼곳"]["값"]:,}원</span></span>'
            f'<span class="row dim">{esc(b["비싼곳"]["지역"])}'
            f'<span class="fig">{b["비싼곳"]["값"]:,}원</span></span>'
            f'<span class="gap fig">{b["도시수"]}개 도시 · 차이 '
            f'{b["차이"]:,}원 ({b["차이율"]}%)</span>'
            '</div>')
    항목.append(f'<div class="col-r">{"".join(오른)}</div>')

    if p.get("단계추적"):
        항목.append(체인(p["단계추적"]))

    묶음 = []
    for 제목, 열쇠 in [("확인", "확인사항"), ("미상", "모르는것")]:
        값 = p.get(열쇠) or []
        if 값:
            줄 = "".join(f"<li>{굵게(v)}</li>" for v in 값)
            묶음.append(f'<span class="k">{제목}</span><ul>{줄}</ul>')
    if 묶음:
        항목.append(f'<div class="notes">{"".join(묶음)}</div>')

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
def 머리숫자(판정들: list[dict]) -> tuple[str, str]:
    """Stat-Led 구조의 머리. **페이지에서 가장 큰 것이 오늘의 답**이다.

    확인이 필요한 품목이 있으면 그 개수를, 없으면 `0`을 크게 쓴다.
    「0」이 크게 보이는 것이 「오늘은 볼 것 없다」를 3초 안에 전한다.
    """
    확인 = sum(1 for p in 판정들 if p.get("확인필요"))
    if 확인:
        return f'{확인}<span class="unit">품목</span>', "up"
    return '0<span class="unit">품목</span>', "calm"


def html으로(보고서: dict) -> str:
    판정들 = 보고서.get("우선검토", [])
    대상월 = (보고서.get("기준일") or "")[4:6] or "07"
    n = len(판정들)
    if 판정들:
        점 = "".join(f'<button class="pip" data-go="{i}" '
                    f'aria-label="{i}번째 품목"></button>' for i in range(n))
        본문 = ('<div class="deck">'
              '<button class="nav prev" data-step="-1" aria-label="이전 품목">←</button>'
              '<div class="viewport"><div class="track">'
              + "".join(카드(p, i, n, 대상월) for i, p in enumerate(판정들, 1))
              + '</div></div>'
              '<button class="nav next" data-step="1" aria-label="다음 품목">→</button>'
              '</div>'
              f'<div class="pager">'
              f'<button class="nav nav-m prev" data-step="-1" '
              f'aria-label="이전 품목">←</button>'
              f'<div class="pips">{점}</div>'
              f'<span class="count fig"><b>1</b> / {n}</span>'
              f'<button class="nav nav-m next" data-step="1" '
              f'aria-label="다음 품목">→</button></div>')
    else:
        본문 = ('<div class="quiet">평소와 다르게 움직인 품목이 없습니다.<br>'
              '오늘은 따로 보실 것이 없습니다.</div>')
    숫자, 색 = 머리숫자(판정들)
    토큰 = (TEMPLATE.parent / "tokens.css").read_text(encoding="utf-8")
    자형 = (TEMPLATE.parent / "fonts.css").read_text(encoding="utf-8")
    채움 = {
        "자형": 자형,
        "토큰": 토큰,
        "기준일": 보고서.get("기준일", ""),
        "생성시각": 보고서.get("생성시각", "")[:16].replace("T", " "),
        "머리숫자": 숫자,
        "머리색": 색,
        "오늘한줄": 굵게(보고서.get("오늘한줄", "")),
        "항목들": 본문,
        "공통유의": "".join(f"<li>{굵게(x)}</li>"
                        for x in 보고서.get("공통유의", [])),
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
