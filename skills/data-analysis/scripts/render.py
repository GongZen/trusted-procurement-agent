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

import paths                                                        # noqa: E402

ROOT = paths.SKILL
TEMPLATE = paths.TEMPLATES / "report.html"
OUTDIR = paths.OUTPUT

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
def 그래프(점들: list[dict], 대상월: str, 구간이름: str = "") -> str:
    """같은 달 값을 **큰 순서로 늘어놓은 막대**로 그린다.

    🔴 **전에는 꺾은선이었고, 그것이 우리가 하지 않는 주장을 했다.**

       선은 「이렇게 흘러왔다」는 추세로 읽힌다. 그런데 우리는 추세를
       주장하지 않는다 — 선행성을 측정하지 않았고 예측하지 않는다고
       화면에 적어 두었다. 전국 중앙값 점선까지 겹쳐 두 선의 교차를
       읽게 만들었는데, 그것도 우리가 말하지 않는 이야기였다.

       우리가 실제로 말하는 것은 **「6년 중 몇 번째」** 하나다. 그러면
       그림도 그것을 그려야 한다. 값을 큰 순서로 늘어놓고 올해만 칠하면,
       **읽는 법을 배울 필요 없이** 순위가 그대로 보인다.

    🔑 **같은 달만 쓴다.** 계절 진폭이 커서 전 구간을 이으면 톱니만 보이고
       연도 간 차이가 묻힌다. 판정도 같은 달끼리이므로 그림과 어긋나지
       않아야 한다. 그 사실을 캡션에 **글로 밝힌다** — 그림만 보고는
       7월끼리라는 것을 알 수 없다.
    """
    같은달 = [p for p in 점들 if p["ym"][4:] == 대상월]
    if len(같은달) < 3:
        return ""

    값 = [p["값"] for p in 같은달]
    연도 = [p["ym"][:4] for p in 같은달]
    올해연 = 연도[-1]
    n = len(값)
    순위 = sorted(값, reverse=True).index(값[-1]) + 1

    # 막대 길이의 기준점 — 0 이 아니라 **가장 싼 해의 90%**에서 시작한다.
    # 0 부터 그리면 6개가 다 비슷해 보여 순위가 안 보인다. 다만 기준선을
    # 감추면 과장이 되므로, 축 아래에 시작값을 적는다.
    바닥 = min(값) * 0.9
    폭 = (max(값) - 바닥) or 1

    줄 = []
    for v, y in sorted(zip(값, 연도), key=lambda x: -x[0]):
        올해냐 = y == 올해연
        길이 = round((v - 바닥) / 폭 * 100, 1)
        줄.append(
            f'<div class="bar{" now" if 올해냐 else ""}">'
            f'<span class="yr fig">{y}</span>'
            f'<span class="track"><span class="fill" style="width:{길이}%"></span></span>'
            f'<span class="val fig">{v:,}</span>'
            f'</div>')

    return (
        f'<figure class="chart">'
        f'<figcaption><span class="cap">{int(대상월)}월끼리만 비교 · '
        f'평년 {n - 1}년 + 올해</span>'
        f'{f"<span class=\'seg\'>{esc(구간이름)}</span>" if 구간이름 else ""}'
        f'</figcaption>'
        f'<div class="bars" role="img" '
        f'aria-label="{int(대상월)}월 값을 큰 순서로 늘어놓음. '
        f'올해는 {n}년 중 {순위}번째">{"".join(줄)}</div>'
        f'<div class="legend-line">'
        f'<span class="lg pick">올해 {올해연}년 — <b>{n}년 중 {순위}번째</b></span>'
        f'</div>'
        f'</figure>')


def 자리(순위표기: str | None) -> str:
    """「6년 중 1번째」. 🔴 **전에는 여기에 「보통 수준」이 박혀 있었다.**

    1번째든 마지막이든 늘 「보통 수준」이 나왔다. 화면이 판정과 무관한
    말을 하고 있었던 것이다. 이 자리에는 우리 판정 축을 그대로 쓴다.

    숫자를 만드는 것이 아니라 이미 판정된 `"1/6"` 을 사람 말로 옮길
    뿐이므로, 렌더러가 계산하지 않는다는 규칙과 어긋나지 않는다.
    """
    try:
        순위, 전체 = (int(v) for v in (순위표기 or "").split("/"))
    except (ValueError, AttributeError):
        return "비교불가"
    if 순위 == 1:
        return f"{전체}년 중 가장 높음"
    if 순위 == 전체:
        return f"{전체}년 중 가장 낮음"
    return f"{전체}년 중 {순위}번째"


# 🔴 원자료의 `se_nm` 은 「중도매」인데 우리 화면은 그 단계를 「도매」라고
#    부른다(가이드 「유통 3단계」). 한 화면에서 같은 것을 두 이름으로
#    부르면 읽는 사람이 다른 것으로 오해한다. 화면 어휘로 통일한다.
구분표 = {"중도매": "도매"}


def 구분말(값: str) -> str:
    return esc(구분표.get(값, 값))


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
            단위 = esc(d.get("단위") or "")
            # 🔴 `관측`(가장 높음·높은 편…)이 **CSS 클래스로만** 쓰이고
            #    화면에는 안 나왔다. 그래서 두 단계가 함께 1번째여도 읽는
            #    사람이 알 수 없었다. 순위를 띠에 직접 적는다.
            값 = (f'<span class="unitk">{단위}</span>'
                 f'<span class="was fig">평년 {d["평년평균"]:,}원</span>'
                 f'<span class="now fig">{d["올해"]:,}원</span>'
                 f'<span class="dt fig">{표기}</span>'
                 f'<span class="rk">{esc(d.get("자리") or "")}</span>')
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
    항목.append(
        f'<span class="move"><span class="movek">{esc(p.get("주인공단계", ""))} '
        f'단계 · {esc(p.get("주인공단위", ""))}</span>'
        f'<span class="rankword">{자리(p.get("주인공순위"))}</span></span></div>')

    # ── 왼쪽: 설명 + 큰 숫자 하나 ──
    왼 = [f'<p class="say">{굵게(p["사람말"])}</p>']
    c = p.get("높은단계")
    if c:
        # 스탯과 해석을 한 덩어리로 둔다 — 숫자와 그 숫자에 대한 해석이
        # 따로 놓이면 눈이 두 번 왕복한다
        # 🔴 이 블록은 **주인공 단계**를 말한다. 전에는 「평년과 가장 벌어진
        #    조건」이라며 소매 세부 구간(서울 깻잎 무농약 · 친환경농산물)을
        #    크게 썼는데, 카드에서 그것만 축이 달랐다. 지역×품종×등급을
        #    이어 붙인 이름도 따로 노는 값들의 나열이라 의미를 못 만들었다.
        단위말 = f" · {esc(c['단위'])}" if c.get("단위") else ""
        속 = [f'<span class="kk">평년보다 높은 단계</span>'
             f'<span class="k">{esc(c["단계"])}<span class="sub2">'
             f'{esc(c["이름"])}{단위말}</span></span>'
             f'<span class="v fig">{esc(c["증감"]).rstrip("%")}'
             f'<span class="u">%</span></span>'
             f'<span class="sub fig">평년 평균 {c["평년"]:,}원 → '
             f'올해 {c["올해"]:,}원</span>']
        if p.get("해석"):
            속.append(f'<p class="read">{굵게(p["해석"])}</p>')
        왼.append(f'<div class="stat">{"".join(속)}</div>')
    elif p.get("해석"):
        왼.append(f'<div class="stat"><p class="read">{굵게(p["해석"])}</p></div>')
    항목.append(f'<div class="col-l">{"".join(왼)}</div>')

    # ── 오른쪽: 그래프 + 그 아래 빈 자리에 「가장 싼 도시」 ──
    오른 = []
    if p.get("시계열"):
        오른.append(그래프(p["시계열"], 대상월, p.get("그린구간", "")))
    b = p.get("도시")
    if b:
        오른.append(
            '<div class="buy">'
            f'<span class="k">도시 간 도매 가격 차이 · {esc(b["조건"])}</span>'
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


def 판정제외(보고서: dict) -> str:
    """🔴 **우리가 고른 수를 우리 입으로 밝힌다.**

    「임의 임계치를 쓰지 않는다」고 적어 두었는데, 최소관측수와 표시
    품목수는 우리가 고른 값이다. 판정을 가르는 선은 아니지만 **말없이
    쓰면 숨긴 임계치**가 된다. 몇 개를 왜 뺐는지 여기서 말한다.
    """
    검증 = 보고서.get("검증", {})
    최소 = 검증.get("최소관측수", "?")
    제외 = 검증.get("제외구간") or {}
    부족, 없음 = 제외.get("과거관측부족", 0), 제외.get("올해관측없음", 0)
    return (f"과거 같은 달 데이터가 <b>{최소}개 미만</b>인 구간은 비교의 실익이 "
            f"없다고 판단하여, 포함하지 않습니다.")


def 근거표(보고서: dict) -> str:
    수집 = 보고서.get("수집", {})
    검증 = 보고서.get("검증", {})
    제외 = 검증.get("제외구간") or {}
    줄 = [
        ("데이터", "공공데이터포털 — 산지공판장 · 도매시장 정산 · 도소매 가격"),
        ("평년 기준가", f"같은 품목·같은 지역·같은 등급의 과거 "
                 f"{보고서.get('설정', {}).get('기준가', {}).get('기준연수', '?')}년 같은 달"),
        ("판정", "올해 값이 평년에서 몇 번째인지"),
        ("판정 제외", f"관측 부족 {제외.get('과거관측부족', 0):,}구간 · "
                  f"올해 관측 없음 {제외.get('올해관측없음', 0):,}구간"),
        ("수집", f"{수집.get('건수', {})} · 호출 {수집.get('호출수', '?')}회"),
    ]
    if 검증.get("경고"):
        줄.append(("확인된 결손", " / ".join(검증["경고"][:3])))
    if 수집.get("실패"):
        줄.append(("수집 실패", f"{len(수집['실패'])}건"))
    return "".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in 줄)


# ── 출력 ─────────────────────────────────────────────────────────────
def 머리숫자(판정들: list[dict]) -> tuple[str, str]:
    """Stat-Led 구조의 머리. **페이지에서 가장 큰 것이 오늘의 답**이다.

    🔴 **아래에 뜬 카드 수와 같아야 한다.** 전에는 「확인필요」(조사한 모든
       도시에서 최고) 개수를 세었는데, 그것은 선정 기준과 **다른 축**이다.
       그래서 카드가 2장 떠 있는데 머리에는 「0 품목」이 찍혔다 —
       화면이 스스로를 부정했다.

       머리는 「오늘 볼 것이 몇 개인가」에 답한다. 그 답은 카드 수다.
       0이면 「0」이 크게 보이고, 그것이 「오늘은 볼 것 없다」가 된다.
    """
    n = len(판정들)
    return f'{n}<span class="unit">품목</span>', ("up" if n else "calm")


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
        본문 = ('<div class="quiet">평년과 크게 다른 품목이 없습니다.<br>'
              '오늘은 따로 확인하실 품목이 없습니다.</div>')
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
        "판정제외": 판정제외(보고서),
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
                    칸.append(f"{n}[{d.get('단위','')}] "
                              f"{d['평년평균']:,}→{d['올해']:,}원"
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
    검증 = 보고서.get("검증", {})
    제외 = 검증.get("제외구간") or {}
    # 🔴 화면(가이드)에서는 분모를 뺐지만 텍스트 산출물에는 남긴다 —
    #    여기가 「자르지 않았다」를 나중에 확인할 수 있는 유일한 기록이다.
    줄.append(f"  판정된 {검증.get('판정품목', '?')}종 중 한 단계라도 평년에서"
              f" 가장 높은 {len(판정들)}종을 올렸습니다. 자르지 않고 자료가 정합니다."
              f" 과거 관측 {검증.get('최소관측수', '?')}개 미만이라 판정하지 않은 구간"
              f" {제외.get('과거관측부족', 0):,}개.")
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
